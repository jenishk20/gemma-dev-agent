class ClicksController < ApplicationController
  # POST /click
  def create
    # The API spec implies a simple registration of a click.
    # We set the timestamp to the current time.
    click = Click.create(timestamp: Time.current)
    
    if click.save
      head :created
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
      # Parse date and set to start of day for consistent comparison
      filter_date = Date.parse(date_param).beginning_of_day
    rescue ArgumentError
      return render json: { error: "Invalid date format" }, status: :bad_request
    end

    # Construct the query based on the direction operator
    # Using Arel or raw SQL fragments for the comparison
    clicks = Click.where("#{direction} ?", filter_date)

    if clicks.exists?
      render json: clicks.select(:id, :timestamp), status: :ok
    else
      render json: { error: "No clicks found" }, status: :not_found
    end
  end
end