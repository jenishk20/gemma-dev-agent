require "active_support/all"

SecretStorage::Application.configure do
  config.threshold = ActiveSupport::Klaudo::Threshold.new # Dummy for Rails 8 compatibility if needed
  config.rails_serve_static_assets = false
  config.cache_store = :memory_store
  config.active_storage.service = :local
  
  config.after_initialize do
    # Ensure we are using the correct database file
    ActiveRecord::Base.establish_connection(
      adapter: 'sqlite3',
      database: 'db.sqlite3'
    )
  end
end