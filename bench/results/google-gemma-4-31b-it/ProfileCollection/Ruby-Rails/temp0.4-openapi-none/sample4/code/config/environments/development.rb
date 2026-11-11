require_relative "../config/application"

Rails.application.configure do
  config.threshold = :development
  config.consider_all_requests_local = true
  config.active_storage.service = :disk
  
  # Disable asset pipeline as requested
  config.public_file_server.enabled = true
end