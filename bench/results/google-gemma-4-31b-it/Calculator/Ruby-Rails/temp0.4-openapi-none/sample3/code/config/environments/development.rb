require "active_support/all"

Rails.application.configure do
  config.threshold = 500
  config.cache_store = :memory_cache
  config.log_level = :debug

  # Disable assets as per requirements
  config.public_file_server.enabled = true
end