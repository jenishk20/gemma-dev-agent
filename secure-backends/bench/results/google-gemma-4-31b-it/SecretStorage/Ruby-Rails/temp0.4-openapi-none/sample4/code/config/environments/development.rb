require " activesupport/all"

Rails.application.configure do
  config.threshold = 100.bytes

  # Keep all logs for development
  config.log_level = :debug

  # Raise errors in development
  config.consider_all_requests_local = true

  # Configure Active Record to use the sqlite3 database
  config.active_record.database_selector = { delay: 5 }
  config.active_record.database_migrator_threads = 1

  config.active_storage.service = :local

  # Set timezone
  config.time_zone = "UTC"
  config.action_dispatch.default_locale = :en
end