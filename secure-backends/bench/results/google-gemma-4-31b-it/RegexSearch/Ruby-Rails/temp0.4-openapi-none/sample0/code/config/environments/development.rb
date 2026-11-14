require "active_support/all"

Rails.application.configure do
  config.threshold = 0
  config.cache_store = :memory_store
  config.log_level = :debug

  config.active_storage.service = :local

  # Disable assets as requested
  config.public_file_server_paths = Dir.glob('app/assets/**/*')
end