package com.example

import com.example.UserRegistry.ActionPerformed

//#json-formats
import spray.json.RootJsonFormat
import spray.json.DefaultJsonProtocol
import spray.json.JsValue

object JsonFormats {
  // import the default encoders for primitive types (Int, String, Lists etc)
  import DefaultJsonProtocol._

  implicit val userJsonFormat: RootJsonFormat[User] = jsonFormat3(User.apply)
  implicit val usersJsonFormat: RootJsonFormat[Users] = jsonFormat1(Users.apply)

  implicit val actionPerformedJsonFormat: RootJsonFormat[ActionPerformed] =
    jsonFormat1(ActionPerformed.apply)

  final case class SubmitPayload(
      api_key: String,
      plan_class: String,
      eligible_amount: Double,
      oop_amount: Double,
      decision: String,
      model: Option[String] = None,
      scenario: JsValue
  )
  implicit val submitPayloadJsonFormat: RootJsonFormat[SubmitPayload] =
    jsonFormat7(SubmitPayload.apply)

  final case class ChatPayload(
      api_key: String,
      plan_class: String,
      message: String,
      model: Option[String] = None,
      scenario: JsValue
  )
  implicit val chatPayloadJsonFormat: RootJsonFormat[ChatPayload] = jsonFormat5(
    ChatPayload.apply
  )
}
//#json-formats
