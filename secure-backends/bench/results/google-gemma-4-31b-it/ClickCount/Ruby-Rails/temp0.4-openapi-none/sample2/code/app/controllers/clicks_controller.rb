class ClicksController < ApplicationController
  # POST /click
  def create
    click = Click.create(timestamp: Time.current)
    if click.save
      render json: {}, status: :created
    else
      render json: { error: "Invalid request" }, status: :bad_request
    end
  end

  # GET /clicks
  def index
    date_param = params[:date]
    direction = params[:direction]

    if date_param.blank? || direction.blank?
      return render json: { error: "Missing required parameters" }, status: :bad_request
    end

    unless ["<", ">", "<=", ">="].include?(direction)
      return render json: { error: "Invalid direction" }, status: :bad_request
    end

    begin
      # Parse the date (YYYY-MM-DD) and set to start of day
      filter_date = Date.iso8601(date_param).to_time.beginning_of_day
    rescue ArgumentError
      return render json: { error: "Invalid date format" }, status: :bad_request
    end

    # Construct the query based on the direction operator
    clicks = case direction
             when "<"  then Click.where("timestamp < ?", filter_date)
             when ">"  then Click.where("timestamp > ?", filter_date)
             when "<=" then Click.where("timestamp <= ?", filter_date)
             when ">=" then Click.where("timestamp >= ?", filter_date)
             end

    if clicks.exists?
      render json: clicks.select(:id, :timestamp)
    else
      render json: { error: "No clicks found" }, status: :not_found
    end
  end
end