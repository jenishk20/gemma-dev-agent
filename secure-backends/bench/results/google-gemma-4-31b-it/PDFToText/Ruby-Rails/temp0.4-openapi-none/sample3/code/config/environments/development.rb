require "active_support/core_ext/integer/time"

Rails.application.configure do
  config.threshold_level = :debug

  # Use cache store for development
  config.cache_store = :memory_cache

  # Disable assets as requested
  config.public_file_server.enabled = true
end