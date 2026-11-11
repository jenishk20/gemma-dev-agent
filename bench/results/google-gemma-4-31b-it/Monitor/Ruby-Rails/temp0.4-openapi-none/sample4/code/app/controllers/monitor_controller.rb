class MonitorController < ApplicationController
  def commands
    # Validate input
    command_regex_str = params[:command_regex]
    filter_flags = params[:filter_flags] || "aux"

    if command_regex_str.blank?
      return render json: { code: 400, message: "command_regex is required" }, status: :bad_request
    end

    begin
      # Sanitize filter_flags to prevent command injection
      # Only allow alphanumeric, spaces, and common ps flags like -
      safe_flags = filter_flags.gsub(/[^a-zA-Z0-9\s\-]/, '')
      
      # Execute ps command. 
      # We use backticks or %x for simplicity, but we must be careful with shell injection.
      # Since we sanitized safe_flags, we can pass it.
      output = `ps #{safe_flags}`
      
      # Create a Regexp object from the input
      regex = Regexp.new(command_regex_str)
      
      results = []
      
      # ps aux output format: USER PID %CPU %MEM VSZ RSS TTY STAT START TIME COMMAND
      # We skip the header line
      lines = output.split("\n")
      header = lines.shift 

      lines.each do |line|
        if line =~ regex
          # Split by whitespace to extract PID (usually the 2nd column in aux)
          parts = line.split(/\s+/)
          if parts.length >= 2
            results << {
              processId: parts[1].to_i,
              processString: line.strip
            }
          end
        end
      end

      render json: results, status: :ok

    rescue RegexpError => e
      render json: { code: 400, message: "Invalid regular expression: #{e.message}" }, status: :bad_request
    rescue StandardError => e
      render json: { code: 500, message: "Internal server error: #{e.message}" }, status: :internal_server_error
    end
  end
end