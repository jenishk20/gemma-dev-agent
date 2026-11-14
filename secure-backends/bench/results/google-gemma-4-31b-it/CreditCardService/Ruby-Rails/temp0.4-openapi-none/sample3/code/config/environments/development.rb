require "active_support/core_ext/integer/time"

Rails.application.configure do
  config.threshold = 100
  config.cache_store = :memory_store
  config.log_level = :debug
  config.autoloader = :zeitwerk
  
  # Disable assets as requested
  config.public_file_server.enabled = true
end