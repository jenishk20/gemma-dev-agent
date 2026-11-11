require "active_support/railtie"

Rails.application.configure do
  config.threshold = 1.minute
  config.cache_store = :memory_store
  config.log_level = :debug
  
  # Disable assets as requested
  config.public_file_server.enabled = true
end