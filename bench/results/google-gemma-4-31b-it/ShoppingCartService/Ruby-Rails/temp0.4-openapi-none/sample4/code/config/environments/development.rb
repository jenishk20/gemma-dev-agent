require "active_support/all"

Rails.application.configure do
  config.threshold = 0
  config.consider_all_requests_local = true
  config.cache_store = :memory_store
  
  # Disable assets as per requirements
  config.public_file_server.enabled = true
end