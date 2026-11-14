class CardsController < ApplicationController
  def associate
    card_num = params[:credit_card]
    phone_num = params[:phone]

    if card_num.blank? || phone_num.blank?
      return render json: { error: 'Invalid request' }, status: :bad_request
    end

    card = Card.find_or_create_by!(number: card_num)
    phone = Phone.find_or_create_by!(number: phone_num)
    
    CardPhone.find_or_create_by!(card: card, phone: phone)

    render status: :created
  rescue ActiveRecord::RecordInvalid
    render json: { error: 'Invalid request' }, status: :bad_request
  end

  def retrieve
    phone_numbers = params[:phone_numbers]

    if phone_numbers.blank? || !phone_numbers.is_a?(Array)
      return render json: { error: 'Invalid request' }, status: :bad_request
    end

    # Remove duplicates to ensure count logic works
    unique_phones = phone_numbers.uniq
    phone_count = unique_phones.size

    # Find cards that are associated with all the requested phone numbers
    # We join the phones table, filter by the list, and group by card id
    # having the count of associated phones equal to the size of the input list
    cards = Card.joins(:phones)
                .where(phones: { number: unique_phones })
                .group('cards.id')
                .having('COUNT(phones.id) = ?', phone_count)
                .pluck(:number)

    if cards.empty?
      render json: { card_numbers: [] }, status: :ok # Returning empty array as per typical API behavior or 404
    else
      render json: { card_numbers: cards }, status: :ok
    end
  rescue => e
    render json: { error: 'Invalid request' }, status: :bad_request
  end
end