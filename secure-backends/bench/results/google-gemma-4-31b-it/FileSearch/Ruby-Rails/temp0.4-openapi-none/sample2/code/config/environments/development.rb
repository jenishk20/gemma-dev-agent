require "active_support/core_ext/integer/time"

Application.configure do
  config.threshold_level = :debug
  config.cache_store = :memory_cache
  
  # Disable assets as requested
  config.public_file_server.enabled = true
end