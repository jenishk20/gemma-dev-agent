require "rails/all"

Rails.application.configure do
  config.load_defaults 8.0.1
  config.too_many_restarts = 0
  config.rails_cache_id = "development"
  
  # Disable assets pipeline as requested
  config.assets.enabled = false
  
  config.active_storage.service = :local
end