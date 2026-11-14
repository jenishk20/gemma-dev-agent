require "rails/all"

Rails.application.configure do
  # Set default source for assets to be compiled
  config.asset_host = nil

  # Set the environment to development
  config.environment_type = :local

  # Use cached expanded paths for faster boot times
  config.cache_store = :memory_store

  # Standard development logging
  config.log_level = :debug

  # Disable assets pipeline as requested
  config.public_file_server.enabled = true
end