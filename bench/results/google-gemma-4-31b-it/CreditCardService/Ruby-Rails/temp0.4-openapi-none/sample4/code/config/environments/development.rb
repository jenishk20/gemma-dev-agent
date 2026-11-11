require "active_support/all"

Rails.application.configure do
  config.threshold = 100
  config.cache_store = :memory

  config.after_initialize do
    # Ensure we use the specific db.sqlite3 file
    ActiveRecord::Base.establish_connection(
      adapter: 'sqlite3',
      database: 'db.sqlite3'
    )
  end
end