require "active_support/all"

Rails.application.configure do
  config.load_defaults 8.0.1

  config.cache = SolidCache.new # Use solid_cache as per Gemfile
  
  # Disable assets as requested
  config.public_file_server.enabled = ActiveStorage::PublicService.enabled?

  # Log to stdout for container environments
  config.logger = ActiveSupport::Logger.new(STDOUT)
  config.log_level = :debug

  # Set database to sqlite3
  config.active_record.database_selector = { a_database_name: :database }
end