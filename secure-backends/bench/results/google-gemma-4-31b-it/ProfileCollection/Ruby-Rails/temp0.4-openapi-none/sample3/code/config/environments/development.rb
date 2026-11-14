require "rails/all"

Rails.application.configure do
  config.threshold_level = :debug
  config.cache_store = :memory_store
  config.log_level = :debug

  # Disable assets pipeline as requested
  config.public_file_server.enabled = true
  
  # Use the local disk for Active Storage
  config.active_storage.service = :local
end