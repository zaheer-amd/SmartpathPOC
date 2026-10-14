package com.example

import akka.actor.typed.ActorRef
import akka.actor.typed.Behavior
import akka.actor.typed.scaladsl.Behaviors
import akka.http.scaladsl.Http
import akka.http.scaladsl.model._
import scala.util.{Success, Failure}
import spray.json._
import spray.json.DefaultJsonProtocol._

object TraineeActor {
  sealed trait Command

  final case class SubmitClaim(
      sessionId: Option[String],
      apiKey: String,
      planClass: String,
      eligible: Double,
      oop: Double,
      decision: String,
      model: Option[String],
      scenario: JsValue,
      replyTo: ActorRef[SubmitResponse]
  ) extends Command

  final case class SubmitChat(
      sessionId: Option[String],
      apiKey: String,
      planClass: String,
      message: String,
      model: Option[String],
      scenario: JsValue,
      replyTo: ActorRef[SubmitResponse]
  ) extends Command

  private final case class WrappedHttpResponse(
      response: HttpResponse, 
      replyTo: ActorRef[SubmitResponse],
      sessionId: Option[String],
      startTime: Long,
      interactionType: String,
      requestPayload: String
  ) extends Command
  
  private final case class WrappedHttpError(
      error: Throwable, 
      replyTo: ActorRef[SubmitResponse]
  ) extends Command
  
  private final case class WrappedStrictEntity(
      status: Int, 
      data: String, 
      replyTo: ActorRef[SubmitResponse],
      sessionId: Option[String],
      startTime: Long,
      interactionType: String,
      requestPayload: String
  ) extends Command

  final case class SubmitResponse(statusCode: Int, payload: String)

  def apply(sessionStore: ActorRef[SessionStore.Command]): Behavior[Command] = Behaviors.setup { context =>
    implicit val system = context.system
    import system.executionContext

    Behaviors.receiveMessage {
      case SubmitClaim(sessionId, apiKey, planClass, eligible, oop, decision, modelOpt, scenario, replyTo) =>
        context.log.info(s"Actor received claim for plan $planClass: $eligible, $oop, $decision, session: $sessionId")
        val startTime = System.currentTimeMillis()

        val baseFields = Map[String, JsValue](
          "api_key" -> JsString(apiKey),
          "plan_class" -> JsString(planClass),
          "eligible_amount" -> JsNumber(eligible),
          "oop_amount" -> JsNumber(oop),
          "decision" -> JsString(decision),
          "scenario" -> scenario
        )
        val withModel = modelOpt.fold(baseFields)(m => baseFields + ("model" -> JsString(m)))
        val withSession = sessionId.fold(withModel)(s => withModel + ("session_id" -> JsString(s)))
        val jsonPayload = JsObject(withSession).compactPrint
        
        val request = HttpRequest(
          method = HttpMethods.POST,
          uri = "http://localhost:8000/evaluate",
          entity = HttpEntity(ContentTypes.`application/json`, jsonPayload)
        )

        val responseFuture = Http().singleRequest(request)
        
        context.pipeToSelf(responseFuture) {
          case Success(response) => WrappedHttpResponse(response, replyTo, sessionId, startTime, "submit", jsonPayload)
          case Failure(ex)       => WrappedHttpError(ex, replyTo)
        }
        Behaviors.same

      case SubmitChat(sessionId, apiKey, planClass, message, modelOpt, scenario, replyTo) =>
        context.log.info(s"Actor received chat message for $planClass, session: $sessionId")
        val startTime = System.currentTimeMillis()
        
        val baseFields = Map[String, JsValue](
          "api_key" -> JsString(apiKey),
          "plan_class" -> JsString(planClass),
          "message" -> JsString(message),
          "scenario" -> scenario
        )
        val withModel = modelOpt.fold(baseFields)(m => baseFields + ("model" -> JsString(m)))
        val withSession = sessionId.fold(withModel)(s => withModel + ("session_id" -> JsString(s)))
        val jsonPayload = JsObject(withSession).compactPrint
        
        val request = HttpRequest(
          method = HttpMethods.POST,
          uri = "http://localhost:8000/chat",
          entity = HttpEntity(ContentTypes.`application/json`, jsonPayload)
        )

        val responseFuture = Http().singleRequest(request)
        
        context.pipeToSelf(responseFuture) {
          case Success(response) => WrappedHttpResponse(response, replyTo, sessionId, startTime, "chat", jsonPayload)
          case Failure(ex)       => WrappedHttpError(ex, replyTo)
        }
        Behaviors.same

      case WrappedHttpResponse(response, replyTo, sessionId, startTime, interactionType, reqPayload) =>
        import scala.concurrent.duration._
        context.pipeToSelf(response.entity.toStrict(60.seconds)) {
          case Success(strictEntity) => WrappedStrictEntity(response.status.intValue, strictEntity.data.utf8String, replyTo, sessionId, startTime, interactionType, reqPayload)
          case Failure(ex) => WrappedHttpError(ex, replyTo)
        }
        Behaviors.same

      case WrappedStrictEntity(status, data, replyTo, sessionId, startTime, interactionType, reqPayload) =>
        val latencyMs = System.currentTimeMillis() - startTime
        
        // Log to SessionStore if we have a session
        sessionId.foreach { sid =>
           sessionStore ! SessionStore.LogInteraction(sid, interactionType, reqPayload, data, latencyMs)
        }
        
        replyTo ! SubmitResponse(status, data)
        Behaviors.same

      case WrappedHttpError(error, replyTo) =>
        context.log.error(s"HTTP request failed: ${error.getMessage}")
        val errPayload = JsObject(
          "success" -> JsBoolean(false),
          "error" -> JsString(error.getMessage)
        ).compactPrint
        replyTo ! SubmitResponse(500, errPayload)
        Behaviors.same
    }
  }
}
