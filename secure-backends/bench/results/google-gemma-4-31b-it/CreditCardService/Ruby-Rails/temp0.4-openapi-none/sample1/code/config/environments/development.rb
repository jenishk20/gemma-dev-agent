require "active_support/all"

Rails.application.configure do
  # Set ActiveRecord adapter to sqlite3
  config.active_record.database_adapter = "sqlite3"
  config.active_record.database_path = "db.sqlite3"

  config. ActiveRecord.raise_on_precision_in_fractional_seconds = false
  
  # Disable assets as requested
  config.public_file_server.enabled = true
  
  # Standard API settings
  config.action_controller.railed_api_only = true
end