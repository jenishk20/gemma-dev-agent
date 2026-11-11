require "rails/all"

Rails.application.configure do
  config.load_defaults 8.0
  config.cache_store = :memory_store
  
  # Disable assets as per requirements
  config.public_file_server.enabled = true
end