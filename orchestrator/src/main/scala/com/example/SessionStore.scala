package com.example

import akka.actor.typed.ActorRef
import akka.actor.typed.Behavior
import akka.actor.typed.scaladsl.Behaviors
import java.sql.{Connection, DriverManager, PreparedStatement, ResultSet}
import java.time.Instant
import java.util.UUID
import scala.util.Using

object SessionStore {

  sealed trait Command

  final case class CreateSession(
      traineeId: String,
      planClass: String,
      replyTo: ActorRef[SessionCreated]
  ) extends Command
  final case class SessionCreated(sessionId: String)

  final case class LogInteraction(
      sessionId: String,
      interactionType: String,
      requestPayload: String,
      responsePayload: String,
      latencyMs: Long
  ) extends Command

  final case class GetSessionHistory(
      sessionId: String,
      replyTo: ActorRef[SessionHistory]
  ) extends Command
  final case class SessionHistory(interactions: Seq[InteractionRecord])
  final case class InteractionRecord(
      id: Int,
      sessionId: String,
      interactionType: String,
      requestPayload: String,
      responsePayload: String,
      timestamp: String,
      latencyMs: Long
  )

  final case class ListSessions(replyTo: ActorRef[SessionsList]) extends Command
  final case class SessionsList(sessions: Seq[SessionInfo])
  final case class SessionInfo(
      sessionId: String,
      traineeId: String,
      planClass: String,
      startedAt: String,
      interactionCount: Int
  )

  def apply(): Behavior[Command] = Behaviors.setup { context =>
    val config = context.system.settings.config
    val dbPath = if (config.hasPath("my-app.session-store.db-path")) {
      config.getString("my-app.session-store.db-path")
    } else {
      "trainee_sessions.db"
    }

    val jdbcUrl = s"jdbc:sqlite:$dbPath"
    
    // Initialize DB schema
    try {
      Class.forName("org.sqlite.JDBC") // Ensure driver is loaded
      Using(DriverManager.getConnection(jdbcUrl)) { conn =>
        val stmt = conn.createStatement()
        stmt.execute("""
          CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            trainee_id TEXT NOT NULL,
            plan_class TEXT NOT NULL,
            started_at TEXT NOT NULL
          )
        """)
        stmt.execute("""
          CREATE TABLE IF NOT EXISTS interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            interaction_type TEXT NOT NULL,
            request_payload TEXT NOT NULL,
            response_payload TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            latency_ms INTEGER NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions(session_id)
          )
        """)
        context.log.info(s"Session DB initialized at $dbPath")
      }
    } catch {
      case e: Exception =>
        context.log.error(s"Failed to initialize Session DB: ${e.getMessage}", e)
    }

    Behaviors.receiveMessage {
      case CreateSession(traineeId, planClass, replyTo) =>
        val sessionId = UUID.randomUUID().toString
        val startedAt = Instant.now().toString
        
        Using(DriverManager.getConnection(jdbcUrl)) { conn =>
          val pstmt = conn.prepareStatement(
            "INSERT INTO sessions (session_id, trainee_id, plan_class, started_at) VALUES (?, ?, ?, ?)"
          )
          pstmt.setString(1, sessionId)
          pstmt.setString(2, traineeId)
          pstmt.setString(3, planClass)
          pstmt.setString(4, startedAt)
          pstmt.executeUpdate()
        }
        
        replyTo ! SessionCreated(sessionId)
        Behaviors.same

      case LogInteraction(sessionId, interactionType, reqPayload, respPayload, latencyMs) =>
        val timestamp = Instant.now().toString
        
        try {
          Using(DriverManager.getConnection(jdbcUrl)) { conn =>
            val pstmt = conn.prepareStatement(
              "INSERT INTO interactions (session_id, interaction_type, request_payload, response_payload, timestamp, latency_ms) VALUES (?, ?, ?, ?, ?, ?)"
            )
            pstmt.setString(1, sessionId)
            pstmt.setString(2, interactionType)
            pstmt.setString(3, reqPayload)
            pstmt.setString(4, respPayload)
            pstmt.setString(5, timestamp)
            pstmt.setLong(6, latencyMs)
            pstmt.executeUpdate()
          }
        } catch {
          case e: Exception =>
            context.log.error(s"Failed to log interaction for session $sessionId: ${e.getMessage}")
        }
        Behaviors.same

      case GetSessionHistory(sessionId, replyTo) =>
        var interactions = Seq.empty[InteractionRecord]
        try {
          Using(DriverManager.getConnection(jdbcUrl)) { conn =>
            val pstmt = conn.prepareStatement(
              "SELECT * FROM interactions WHERE session_id = ? ORDER BY id ASC"
            )
            pstmt.setString(1, sessionId)
            val rs = pstmt.executeQuery()
            while (rs.next()) {
              interactions = interactions :+ InteractionRecord(
                id = rs.getInt("id"),
                sessionId = rs.getString("session_id"),
                interactionType = rs.getString("interaction_type"),
                requestPayload = rs.getString("request_payload"),
                responsePayload = rs.getString("response_payload"),
                timestamp = rs.getString("timestamp"),
                latencyMs = rs.getLong("latency_ms")
              )
            }
          }
        } catch {
           case e: Exception =>
             context.log.error(s"Error getting session history: ${e.getMessage}")
        }
        replyTo ! SessionHistory(interactions)
        Behaviors.same

      case ListSessions(replyTo) =>
        var sessions = Seq.empty[SessionInfo]
        try {
          Using(DriverManager.getConnection(jdbcUrl)) { conn =>
            val stmt = conn.createStatement()
            val rs = stmt.executeQuery("""
              SELECT s.session_id, s.trainee_id, s.plan_class, s.started_at, COUNT(i.id) as interactionCount
              FROM sessions s
              LEFT JOIN interactions i ON s.session_id = i.session_id
              GROUP BY s.session_id
              ORDER BY s.started_at DESC
            """)
            while (rs.next()) {
              sessions = sessions :+ SessionInfo(
                sessionId = rs.getString("session_id"),
                traineeId = rs.getString("trainee_id"),
                planClass = rs.getString("plan_class"),
                startedAt = rs.getString("started_at"),
                interactionCount = rs.getInt("interactionCount")
              )
            }
          }
        } catch {
           case e: Exception =>
             context.log.error(s"Error listing sessions: ${e.getMessage}")
        }
        replyTo ! SessionsList(sessions)
        Behaviors.same
    }
  }
}
