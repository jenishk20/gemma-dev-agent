require "active_support/all"

Rails.application.configure do
  config.threshold = 0
  config.cache_store = :memory_cache
  config.log_level = :debug

  config.after_initialize do
    # Ensure the /data directory exists for the search functionality
    FileUtils.mkdir_p('/data') unless Dir.exist?('/data')
  end
end