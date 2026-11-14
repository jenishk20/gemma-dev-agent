require "active_support/all"

Rails.application.configure do
  config.load_defaults 8.0

  # Use SQLite for development
  config.active_record.database_selector = { delay: 5 }
  config.active_record.database_migrator_threads = 1

  config.cache_store = :memory_cache
  config.log_level = :debug

  # Disable assets as per requirements
  config.public_file_server.enabled = true
end