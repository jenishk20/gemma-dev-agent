class MonitorController < ApplicationController
  def commands
    # Validate request body
    command_regex = params[:command_regex]
    filter_flags = params[:filter_flags] || ""

    if command_regex.blank?
      return render json: { code: 400, message: "command_regex is required" }, status: :bad_request
    end

    begin
      # Sanitize filter_flags to prevent command injection
      # Only allow alphanumeric, spaces, and common ps flags (-, a-z, A-Z)
      safe_flags = filter_flags.gsub(/[^a-zA-Z0-9\s\-]/, '')
      
      # Construct the ps command. 
      # Since 'command' parameter is not supported, we use standard ps output.
      # We use 'ps' with the provided flags.
      cmd = "ps #{safe_flags}"
      output = `#{cmd}`

      # Create a regex object from the user input
      regex = Regexp.new(command_regex)
      
      results = []
      
      # ps output usually starts with a header. We split by lines.
      lines = output.split("\n")
      
      # Skip header (usually the first line)
      lines[1..-1]&.each do |line|
        if line =~ regex
          # Extract PID. In most 'ps' outputs, the PID is the first integer found in the line.
          # We split by whitespace and find the first numeric element.
          parts = line.split(/\s+/)
          pid = parts.find { |p| p =~ /^\d+$/ }
          
          if pid
            results << {
              processId: pid.to_i,
              processString: line.strip
            }
          end
        end
      end

      render json: results
    rescue RegexpError => e
      render json: { code: 400, message: "Invalid regular expression: #{e.message}" }, status: :bad_request
    rescue StandardError => e
      render json: { code: 500, message: "Internal server error: #{e.message}" }, status: :internal_server_error
    end
  end
end