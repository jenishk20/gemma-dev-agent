require "active_support/core_ext/integer/time"

Rails.application.configure do
  # Keep all logger output within the logs directory
  config.logger = ActiveSupport::Logger.new(STDOUT)
  config.log_level = :debug

  # Configure Active Record to be looser in development
  config.active_record.dump_schema_after_migration = false

  # Disable assets pipeline as requested
  config.public_file_server.enabled = true
end