require "rails/all"

Rails.application.configure do
  # Keep the development environment simple
  config.cache_store = :memory_cache
  config.log_level = :debug

  # Disable asset pipeline as requested
  config.public_file_server.enabled = true
end