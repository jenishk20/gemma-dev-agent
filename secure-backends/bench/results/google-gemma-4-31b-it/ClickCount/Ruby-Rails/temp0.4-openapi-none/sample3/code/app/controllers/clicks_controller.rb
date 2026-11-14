class ClicksController < ApplicationController
  # POST /click
  def create
    # Register a click with the current time
    click = Click.create(timestamp: Time.current)
    
    if click.persisted?
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
      return render json: { error: "Missing date or direction parameters" }, status: :bad_request
    end

    unless ["<", ">", "<=", ">="].include?(direction)
      return render json: { error: "Invalid direction operator" }, status: :bad_request
    end

    begin
      # Parse date and ensure it's treated as the start of that day
      filter_date = Date.parse(date_param).beginning_of_day
    rescue ArgumentError
      return render json: { error: "Invalid date format" }, status: :bad_request
    end

    # Construct the query based on the direction operator
    # Using Arel or raw SQL fragments for the comparison
    clicks = case direction
              when "<"  then Click.where("timestamp < ?", filter_date)
              when ">"  then Click.where("timestamp > ?", filter_date)
              when "<=" then Click.where("timestamp <= ?", filter_date)
              when ">=" then Click.where("timestamp >= ?", filter_date)
              end

    if clicks.empty?
      render json: { error: "No clicks found" }, status: :not_found
    else
      # Return only id and timestamp as per schema
      render json: clicks.select(:id, :timestamp)
    end
  end
end