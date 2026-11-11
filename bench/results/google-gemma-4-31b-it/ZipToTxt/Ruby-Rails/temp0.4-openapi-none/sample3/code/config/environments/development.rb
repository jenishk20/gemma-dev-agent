require "active_support/all"

Rails.application.configure do
  config.threshold = 100.bytes

  config.rails_serve_static_assets = false

  # Use SQLite for development
  config.active_storage.service = :local
end