require "environments/development"

Rails.application.configure do
  # Set ActiveRecord adapter to SQLite3
  config.active_record.database_adapter = "sqlite3"

  # Set default logger
  config.logger = ActiveSupport::Logger.new(STDOUT)

  # Set default Rails environment to development
  config.env_class = "development"

  # Disable caching for development
  config.action_controller.perform_caching = false
  config.cache_store = :memory_store

  # Ensure we don't use assets pipeline
  config.public_file_server.enabled = true
end