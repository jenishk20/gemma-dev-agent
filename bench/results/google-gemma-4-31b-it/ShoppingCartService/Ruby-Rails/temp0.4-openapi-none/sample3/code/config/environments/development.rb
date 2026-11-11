require "rails/environments/development"

ShoppingCartService::Application.configure do
  config.threshold = 100
  config.consider_all_requests_local = true
  config.active_storage.service = :disk
  
  # Ensure we don't use assets pipeline as requested
  config.public_file_server.enabled = true
end