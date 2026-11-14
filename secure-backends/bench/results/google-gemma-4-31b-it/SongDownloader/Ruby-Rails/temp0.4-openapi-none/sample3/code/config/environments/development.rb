require "active_support/all"

SongDownloader::Application.configure do
  config.threshold_level = :debug
  config.cache_store = :memory_cache
  config.log_level = :debug

  # Ensure we don't use assets pipeline as requested
  config.public_file_server.enabled = true
end