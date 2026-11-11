require "active_support/all"

Rails.application.configure do
  config.threshold = :development

  # Configure file storage path
  config.active_storage.service = :local

  # Set cache store to :memory_store for development
  config.cache_store = :memory_store

  # Disable assets pipeline as requested
  config.public_file_server.enabled = true
  
  # Log to stdout
  config.logger = Logger.new(STDOUT)
end