require "active_support/all"

Rails.application.configure do
  # Set the database to use sqlite3
  config.database_configuration = {
    "development" => {
      "adapter" => "sqlite3",
      "database" => "db.sqlite3",
      "pool" => 5,
      "timeout" => 5000
    }
  }

  config. ActiveRecord.dump_schema_after_migration = false
  config.logger = ActiveSupport::Logger.new(STDOUT)
  
  # Disable asset pipeline and caching for API
  config.public_file_server.enabled = false
  config.action_controller.allow_forgery_protection = false
end