require "active_support/all"

Rails.application.configure do
  # Configure waitress or puma
  config.rails_serve_static_assets = false

  # Set database to sqlite3
  config.active_record.database_selector = { a: :production }
  
  config.cache_store = :memory_cache
end