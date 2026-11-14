class ClicksController < ApplicationController
  # POST /click
  def create
    # The schema doesn't specify a body, but usually, a click is registered at the moment of request.
    # We set the timestamp to the current time.
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
      return render json: { error: "Invalid direction. Use <, >, <=, or >=" }, status: :bad_request
    end

    begin
      # Parse date and set to start of day for comparison
      filter_date = Date.iso8601(date_param).to_time
    rescue ArgumentError
      return render json: { error: "Invalid date format. Use YYYY-MM-DD" }, status: :bad_request
    end

    # Construct the query based on the operator
    # We use Arel or raw SQL string for the comparison operator
    clicks = Click.where("#{direction} ?", filter_date)

    if clicks.empty?
      render json: { error: "No clicks found" }, status: :not_found
    else
      # Map to the schema: only return id and timestamp
      render json: clicks.map { |c| { id: c.id.to_s, timestamp: c.timestamp.iso8601 } }
    end
  end
end