require "rails/all"

Rails.application.configure do
  # Set default adapter for all caches
  config.cache_store = :memory_cache

  # Use the database-backed active storage
  config.active_storage.service = :local

  # Set the server port and binding
  config.server = { binding: '0.0.0.0', port: 5000 }

  # Log level
  config.log_level = :debug
end