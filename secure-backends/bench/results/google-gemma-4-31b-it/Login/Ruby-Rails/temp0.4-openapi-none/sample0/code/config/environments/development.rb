require "active_support/core_ext/integer/time"

Rails.application.configure do
  # Keep the app in development mode
  config.threshold = 1.second

  # Use cached expanded paths for all action controllers
  config.action_controller.action_cable.disable_request_forgery = true

  # Set database to sqlite3
  config.active_record.database_selector = { a: 'db.sqlite3' }
  
  # Disable assets pipeline as requested
  config.public_file_server.enabled = true
end