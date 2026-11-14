require "rails/all"

Rails.application.configure do
  config.threshold = 0
  config.cache = :memory

  # Disable assets as requested
  config.public_file_server.enabled = true
  
  config.consider_all_requests_local = true
  config.active_storage.service = :local
end