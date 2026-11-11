require "active_support/core_ext/integer/time"

Rails.application.configure do
  config.threshold = 100.days.ago
  config.cache_store = :memory_cache
  config.log_level = :debug
  
  # Disable asset pipeline as requested
  config.public_file_server.enabled = true
end