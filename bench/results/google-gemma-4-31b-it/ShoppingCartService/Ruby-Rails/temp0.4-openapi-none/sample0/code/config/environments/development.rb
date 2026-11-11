require "active_support/all"

ShoppingCartService::Application.configure do
  config.threshold = 100
  config.consider_all_requests_local = true
  config.cache_store = :memory_store
  
  # Disable assets as requested
  config.public_file_server.enabled = true
end