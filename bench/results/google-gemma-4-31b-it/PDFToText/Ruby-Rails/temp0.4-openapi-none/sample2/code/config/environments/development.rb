require "active_support/core_ext/integer/time"

Rails.application.configure do
  config.threshold = 100
  config.cache_store = :memory_cache
  config.after_initialize do
    ActiveRecord::Base.establish_connection(adapter: 'sqlite3', database: 'db.sqlite3')
  end
  config.active_storage.service = :local
end