package com.example

import spray.json.RootJsonFormat
import spray.json.DefaultJsonProtocol
import spray.json.JsValue

object JsonFormats {
  import DefaultJsonProtocol._

  final case class SubmitPayload(
      api_key: String,
      plan_class: String,
      eligible_amount: Double,
      oop_amount: Double,
      decision: String,
      model: Option[String] = None,
      scenario: JsValue,
      session_id: Option[String] = None
  )
  implicit val submitPayloadJsonFormat: RootJsonFormat[SubmitPayload] =
    jsonFormat8(SubmitPayload.apply)

  final case class ChatPayload(
      api_key: String,
      plan_class: String,
      message: String,
      model: Option[String] = None,
      scenario: JsValue,
      session_id: Option[String] = None
  )
  implicit val chatPayloadJsonFormat: RootJsonFormat[ChatPayload] = jsonFormat6(
    ChatPayload.apply
  )

  final case class StartSessionPayload(trainee_id: String, plan_class: String)
  implicit val startSessionFormat: RootJsonFormat[StartSessionPayload] = jsonFormat2(StartSessionPayload.apply)

  final case class SessionCreatedResponse(session_id: String)
  implicit val sessionCreatedFormat: RootJsonFormat[SessionCreatedResponse] = jsonFormat1(SessionCreatedResponse.apply)

  implicit val interactionRecordFormat: RootJsonFormat[SessionStore.InteractionRecord] = jsonFormat7(SessionStore.InteractionRecord.apply)
  implicit val sessionHistoryFormat: RootJsonFormat[SessionStore.SessionHistory] = jsonFormat1(SessionStore.SessionHistory.apply)

  implicit val sessionInfoFormat: RootJsonFormat[SessionStore.SessionInfo] = jsonFormat5(SessionStore.SessionInfo.apply)
  implicit val sessionsListFormat: RootJsonFormat[SessionStore.SessionsList] = jsonFormat1(SessionStore.SessionsList.apply)
}
