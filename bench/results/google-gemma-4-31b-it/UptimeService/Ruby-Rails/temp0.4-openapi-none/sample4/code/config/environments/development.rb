require "active_support/all"

Rails.application.configure do
  config.threshold = 100
  config.cache_store = :memory_store
  config.log_level = :debug

  # Disable assets as requested
  config.public_file_server.enabled = true
  
  # Ensure we don't use sprockets or asset pipeline
  config.assets.enabled = false if config.respond_to?(:assets)
end