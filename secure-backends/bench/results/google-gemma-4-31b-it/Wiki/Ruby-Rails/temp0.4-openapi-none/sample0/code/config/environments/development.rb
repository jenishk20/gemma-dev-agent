require "active_support/all"

Rails.application.configure do
  config.threshold = 0
  config.consider_all_requests_local = true
  config.cache_store = :memory_cache
  
  # Disable assets as requested
  config.assets.enabled = false if config.respond_to?(:assets)
end