package com.example

import akka.http.scaladsl.server.Directives._
import akka.http.scaladsl.model.StatusCodes
import akka.http.scaladsl.server.Route
import akka.http.scaladsl.model._
import akka.http.scaladsl.model.headers._

import akka.actor.typed.ActorRef
import akka.actor.typed.ActorSystem
import akka.actor.typed.scaladsl.AskPattern._
import akka.util.Timeout

class UserRoutes(traineeActor: ActorRef[TraineeActor.Command], sessionStore: ActorRef[SessionStore.Command])(implicit val system: ActorSystem[_]) {

  import akka.http.scaladsl.marshallers.sprayjson.SprayJsonSupport._
  import JsonFormats._

  private implicit val timeout: Timeout = Timeout.create(system.settings.config.getDuration("my-app.routes.ask-timeout"))

  val corsHeaders = List(
    `Access-Control-Allow-Origin`.*,
    `Access-Control-Allow-Methods`(HttpMethods.GET, HttpMethods.POST, HttpMethods.OPTIONS),
    `Access-Control-Allow-Headers`("Content-Type")
  )

  val userRoutes: Route = respondWithHeaders(corsHeaders) {
    concat(
      path("submit") {
        post {
          entity(as[JsonFormats.SubmitPayload]) { payload =>
            onSuccess(traineeActor.ask(TraineeActor.SubmitClaim(payload.session_id, payload.api_key, payload.plan_class, payload.eligible_amount, payload.oop_amount, payload.decision, payload.model, payload.scenario, _))) { response =>
              val statusCode = StatusCodes.getForKey(response.statusCode).getOrElse(StatusCodes.InternalServerError)
              complete(HttpResponse(statusCode, entity = HttpEntity(ContentTypes.`application/json`, response.payload)))
            }
          }
        }
      },
      path("chat") {
        post {
          entity(as[JsonFormats.ChatPayload]) { payload =>
            onSuccess(traineeActor.ask(TraineeActor.SubmitChat(payload.session_id, payload.api_key, payload.plan_class, payload.message, payload.model, payload.scenario, _))) { response =>
              val statusCode = StatusCodes.getForKey(response.statusCode).getOrElse(StatusCodes.InternalServerError)
              complete(HttpResponse(statusCode, entity = HttpEntity(ContentTypes.`application/json`, response.payload)))
            }
          }
        }
      },
      path("session" / "start") {
        post {
          entity(as[StartSessionPayload]) { payload =>
            onSuccess(sessionStore.ask(SessionStore.CreateSession(payload.trainee_id, payload.plan_class, _))) { created =>
              complete(SessionCreatedResponse(created.sessionId))
            }
          }
        }
      },
      path("session" / Segment / "history") { sessionId =>
        get {
          onSuccess(sessionStore.ask(SessionStore.GetSessionHistory(sessionId, _))) { history =>
            complete(history)
          }
        }
      },
      path("sessions") {
        get {
          onSuccess(sessionStore.ask(SessionStore.ListSessions(_))) { sessions =>
            complete(sessions)
          }
        }
      }
    )
  }
}
