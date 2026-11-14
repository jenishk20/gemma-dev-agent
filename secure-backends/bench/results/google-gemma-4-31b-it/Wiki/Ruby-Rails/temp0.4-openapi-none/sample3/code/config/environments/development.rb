require "rails/all"

Rails.application.configure do
  config.load_defaults 8.0
  config.cache_store = :memory_store
  config.active_storage.service = :local
  
  # Disable asset pipeline as requested
  config.public_file_server_views = false
end