require "active_support/all"

Rails.application.configure do
  config.load_defaults 8.0

  config.cache_store = :memory_cache
  config.active_storage.service = :local

  config.logging.logger = Logger.new(STDOUT)

  # Disable assets as per requirements
  config.public_file_server.enabled = true
end