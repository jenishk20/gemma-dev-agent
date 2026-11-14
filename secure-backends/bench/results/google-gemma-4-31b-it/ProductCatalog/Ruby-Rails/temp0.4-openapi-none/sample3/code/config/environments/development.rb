require " activesupport/all"

Rails.application.configure do
  config.threshold = 1.day
  config.cache_store = :memory_store
  
  # Disable assets as requested
  config.public_file_server.enabled = true
  
  config.active_storage.service = :local
  
  # Set logger
  config.log_level = :debug
end