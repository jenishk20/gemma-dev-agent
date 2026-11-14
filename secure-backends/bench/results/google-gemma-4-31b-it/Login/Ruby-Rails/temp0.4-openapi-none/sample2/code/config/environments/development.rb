require "active_support/on_load_resources"

Rails.application.configure do
  # Set Rails environment
  config.load_defaults 8.0

  # Configure watch files for changes to the application
  config.cache_classes = false

  # Configure active storage adapter to disk for development
  config.active_storage.service = :local

  # Set quiet mode
  config.log_level = :debug
end