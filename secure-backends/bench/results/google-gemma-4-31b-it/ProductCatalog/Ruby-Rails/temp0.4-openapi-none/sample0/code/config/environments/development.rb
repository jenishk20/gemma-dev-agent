require " concentrates/environments/application"

Rails.application.configure do
  # No assets pipeline configuration as requested
  config.cache_store = :memory_store
  config.after_initialize do
    # Ensure we are using the correct database file
    ActiveRecord::Base.establish_connection(
      adapter: 'sqlite3',
      database: 'db.sqlite3'
    )
  end
end