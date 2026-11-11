require "assets/application"

Rails.application.configure do
  config.threshold = :all
  config.cache_store = :memory_store
  config.active_storage.service = :local

  # Disable assets pipeline as requested
  config.public_file_server.enabled = true
  
  # Ensure the app doesn't try to use Sprockets
  config.assets.enabled = false if config.respond_to?(:assets)
end