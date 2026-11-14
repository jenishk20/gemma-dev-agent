class LogsController < ApplicationController
  LOG_FILE = Rails.root.join('logs.txt')

  # POST /log
  def create
    message = params[:message]
    
    if message.present?
      File.open(LOG_FILE, 'a') do |f|
        f.puts message
      end
      render json: {}, status: :ok
    else
      render json: { error: "Message is required" }, status: :bad_request
    end
  end

  # GET /logs
  def index
    if File.exist?(LOG_FILE)
      content = File.read(LOG_FILE)
      render plain: content
    else
      render plain: "", status: :ok
    end
  end
end