require "active_support/core_ext/sloggable"

module MyForum
  class Development < Rails::Application
    config.load_defaults 8.0

    config.cache_store = :memory_cache
    config.log_level = :debug

    # Use the database-backed adapter for Rails.cache
    # config.cache_store = SolidCache
  end
end