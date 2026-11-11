require "active_support/core_ext/slicing"

Rails.application.configure do
  # Set to development mode
  config.load_defaults 8.0

  # Use SQLite3 database
  config.active_record.database_selector = { dynamic: true }
  config.active_record.database_shared_cache_after_fork = true

  # Disable assets pipeline as requested
  config.public_file_server.enabled = true
  
  # Log to stdout
  config.logger = ActiveSupport::Logger.new(STDOUT)
end