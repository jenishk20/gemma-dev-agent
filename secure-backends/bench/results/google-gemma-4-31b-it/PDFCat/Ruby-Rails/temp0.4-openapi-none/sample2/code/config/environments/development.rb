require_relative "../application"

Rails.application.configure do
  # Keep it simple for the API service
  config.cache_store = :memory_cache
  config.log_level = :debug
end