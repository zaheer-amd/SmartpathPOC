package com.example

import akka.actor.typed.ActorRef
import akka.actor.typed.Behavior
import akka.actor.typed.scaladsl.Behaviors
import akka.http.scaladsl.Http
import akka.http.scaladsl.model._
import scala.util.{Success, Failure}

object TraineeActor {
  sealed trait Command
  final case class SubmitClaim(
      apiKey: String,
      planClass: String,
      eligible: Double,
      oop: Double,
      decision: String,
      model: Option[String],
      replyTo: ActorRef[SubmitResponse]
  ) extends Command

  final case class SubmitChat(
      apiKey: String,
      planClass: String,
      message: String,
      model: Option[String],
      replyTo: ActorRef[SubmitResponse]
  ) extends Command

  private final case class WrappedHttpResponse(response: HttpResponse, replyTo: ActorRef[SubmitResponse]) extends Command
  private final case class WrappedHttpError(error: Throwable, replyTo: ActorRef[SubmitResponse]) extends Command
  private final case class WrappedStrictEntity(status: Int, data: String, replyTo: ActorRef[SubmitResponse]) extends Command

  final case class SubmitResponse(statusCode: Int, payload: String)

  def apply(): Behavior[Command] = Behaviors.setup { context =>
    implicit val system = context.system
    import system.executionContext

    Behaviors.receiveMessage {
      case SubmitClaim(apiKey, planClass, eligible, oop, decision, modelOpt, replyTo) =>
        context.log.info(s"Actor received claim for plan $planClass: $eligible, $oop, $decision, model: $modelOpt")

        val modelField = modelOpt.map(m => s""", "model": "$m"""").getOrElse("")
        val jsonPayload = s"""{"api_key": "$apiKey", "plan_class": "$planClass", "eligible_amount": $eligible, "oop_amount": $oop, "decision": "$decision"$modelField}"""
        
        val request = HttpRequest(
          method = HttpMethods.POST,
          uri = "http://localhost:8000/evaluate",
          entity = HttpEntity(ContentTypes.`application/json`, jsonPayload)
        )

        val responseFuture = Http().singleRequest(request)
        
        context.pipeToSelf(responseFuture) {
          case Success(response) => WrappedHttpResponse(response, replyTo)
          case Failure(ex)       => WrappedHttpError(ex, replyTo)
        }
        Behaviors.same

      case SubmitChat(apiKey, planClass, message, modelOpt, replyTo) =>
        context.log.info(s"Actor received chat message for $planClass: $message, model: $modelOpt")
        
        val escapedMessage = message.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n").replace("\r", "")
        val modelField = modelOpt.map(m => s""", "model": "$m"""").getOrElse("")
        val jsonPayload = s"""{"api_key": "$apiKey", "plan_class": "$planClass", "message": "$escapedMessage"$modelField}"""
        
        val request = HttpRequest(
          method = HttpMethods.POST,
          uri = "http://localhost:8000/chat",
          entity = HttpEntity(ContentTypes.`application/json`, jsonPayload)
        )

        val responseFuture = Http().singleRequest(request)
        
        context.pipeToSelf(responseFuture) {
          case Success(response) => WrappedHttpResponse(response, replyTo)
          case Failure(ex)       => WrappedHttpError(ex, replyTo)
        }
        Behaviors.same

      case WrappedHttpResponse(response, replyTo) =>
        import scala.concurrent.duration._
        context.pipeToSelf(response.entity.toStrict(60.seconds)) {
          case Success(strictEntity) => WrappedStrictEntity(response.status.intValue, strictEntity.data.utf8String, replyTo)
          case Failure(ex) => WrappedHttpError(ex, replyTo)
        }
        Behaviors.same

      case WrappedStrictEntity(status, data, replyTo) =>
        replyTo ! SubmitResponse(status, data)
        Behaviors.same

      case WrappedHttpError(error, replyTo) =>
        context.log.error(s"HTTP request failed: ${error.getMessage}")
        val errPayload = s"""{"success": false, "error": "${error.getMessage.replace("\"", "\\\"")}"}"""
        replyTo ! SubmitResponse(500, errPayload)
        Behaviors.same
    }
  }
}
